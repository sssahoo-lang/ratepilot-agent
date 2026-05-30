import anthropic
import json
import re
from typing import Optional

client = anthropic.Anthropic(timeout=30.0)
MODEL = "claude-sonnet-4-20250514"


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


def parse_bill(raw_text: str) -> dict:
    """Use Claude to extract structured data from bill text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system="""You are a bill parsing expert. Extract structured data from bill text.
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
        messages=[{"role": "user", "content": f"Parse this bill:\n\n{raw_text}"}]
    )
    return extract_json(response.content[0].text)


def research_competitors(provider: str, bill_type: str, current_amount: float, line_count: int = 1) -> dict:
    """Use Claude with web search to find competitor pricing."""
    line_count = int(line_count or 1)
    account_context = ""
    if line_count > 1:
        account_context = (
            f"\nIMPORTANT: This is a {line_count}-LINE FAMILY/GROUP ACCOUNT. "
            f"You MUST search for and compare {line_count}-line family plan pricing only. "
            "Do NOT use single-line pricing — it is not comparable and will make the negotiation invalid. "
            f"Search specifically for: '{provider} {line_count} lines price 2025' and competitor family plan pricing for {line_count} lines."
        )

    # LIVE WEB SEARCH - retrieves real-time competitor pricing
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system="""You are a market research expert helping consumers negotiate better prices.
Search for current competitor pricing and promotions for the given provider and service type.
After searching, return ONLY a JSON object:
{
  "competitor_prices": [
    {"provider": "name", "price": 49.99, "plan": "description", "promo": "details or null"}
  ],
  "market_average": 65.00,
  "current_promotions": ["list of active promos for the main provider if found"],
  "price_trend": "rising/falling/stable",
  "leverage_points": ["specific facts that give the customer negotiation leverage"],
  "recommended_target": 55.00,
  "walkaway_threshold": 75.00,
  "plan_context": "family-6-lines or individual",
  "research_summary": "2-3 sentence summary of findings"
}
No preamble. JSON only.""",
        messages=[{
            "role": "user",
            "content": f"Research competitors for: {provider} {bill_type} service. Current monthly bill: ${current_amount}. Find current competitor pricing and promotions.{account_context}"
        }],
        tools=[{"type": "web_search_20250305", "name": "web_search"}]
    )
    text_blocks = []
    for block in response.content:
        if block.type == "text":
            text_blocks.append(block.text)
    return extract_json("\n".join(text_blocks)) if text_blocks else {}


def build_strategy(bill_data: dict, research: dict) -> dict:
    """Use Claude to build a negotiation strategy."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system="""You are a master negotiator. Build a detailed negotiation strategy.
Return ONLY a JSON object:
{
  "opening_ask": 49.99,
  "target_price": 55.00,
  "walkaway_threshold": 75.00,
  "primary_leverage": "the single strongest argument",
  "leverage_points": ["ranked list of arguments to use"],
  "tone": "firm/collaborative/urgent",
  "key_phrases": ["specific phrases to include in the email"],
  "anticipated_responses": [
    {"response_type": "rejection", "counter_strategy": "what to do"},
    {"response_type": "partial_offer", "counter_strategy": "what to do"},
    {"response_type": "acceptance", "counter_strategy": "accept"}
  ],
  "strategy_summary": "2-3 sentence explanation of the approach"
}
No preamble. JSON only.""",
        messages=[{
            "role": "user",
            "content": f"""Bill data: {json.dumps(bill_data)}
Research findings: {json.dumps(research)}
Build the optimal negotiation strategy."""
        }]
    )
    return extract_json(response.content[0].text)


def draft_negotiation_email(bill_data: dict, research: dict, strategy: dict, round_num: int = 1, previous_response: Optional[str] = None) -> dict:
    """Use Claude to draft a negotiation email."""
    account_number = bill_data.get("account_number") or "account on file"
    line_count = int(bill_data.get("line_count") or 1)
    line_context = ""
    if line_count > 1:
        line_context = (
            f"\nThis customer has {line_count} lines. Frame all competitor comparisons using {line_count}-line family plan pricing. "
            f"Mention that switching {line_count} lines simultaneously, especially with active device installment plans, is a major disruption — use this as negotiation leverage."
        )
    context = f"""Account number: {account_number}
Bill data: {json.dumps(bill_data)}
Research: {json.dumps(research)}
Strategy: {json.dumps(strategy)}
Round: {round_num}"""
    if previous_response:
        context += f"\nTheir previous response: {previous_response}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=f"""You are an expert negotiator drafting customer retention emails.
Write professional, firm but polite emails that cite specific competitor prices.
IMPORTANT: Use ONLY the exact account number provided below. Never invent or guess an account number. If none is provided, write 'account on file' instead.
IMPORTANT: Always include the customer's full account number, full name, and specific plan details from the bill data.
Never use placeholders like [Customer Name] or "Account #1503 Customer".
Use the EXACT full name and EXACT full account number from the bill_data provided.
Sign the email with the real customer name. End with full account number in the signature.{line_context}
Return ONLY a JSON object:
{{
  "subject": "email subject line",
  "body": "full email body with real account details",
  "key_arguments_used": ["list of main points made"],
  "ask_amount": 49.99,
  "reasoning": "why this approach for this round"
}}
No preamble. JSON only.""",
        messages=[{"role": "user", "content": context}]
    )
    return extract_json(response.content[0].text)


def interpret_response(response_text: str, strategy: dict, history: list) -> dict:
    """Use Claude to interpret a company's response and decide next action."""
    response = client.messages.create(
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
    response = client.messages.create(
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
    response = client.messages.create(
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
