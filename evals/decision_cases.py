"""
Test cases for interpret_response() decision logic.

Each case has:
  reply      - the provider's actual reply text
  strategy   - dict with target_price and walkaway_threshold (and other fields the prompt sees)
  history    - list of prior steps (same shape the app passes)
  expected   - SET of acceptable decisions; runner passes if got is in expected
  guardrail_no_accept - if True, decision must also NOT be "accept" (hard guardrail)
  rationale  - why this expected outcome is correct (for human review)

target_price    = the monthly rate we are aiming for (ideal)
walkaway_threshold = the highest monthly rate we will accept; above this we counter/escalate
"""

CASES = [
    {
        "name": "offer_exactly_at_target",
        "reply": (
            "After reviewing your account, we are pleased to offer you a rate of "
            "$65/month for your internet service. This is our best retention rate."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"accept"},
        "guardrail_no_accept": False,
        "rationale": (
            "Offer of $65 exactly meets the target. Nothing to gain by countering; "
            "accept immediately."
        ),
    },
    {
        "name": "offer_below_target",
        "reply": (
            "We value your long-term loyalty. We'd like to offer you a special rate "
            "of $59/month starting on your next billing cycle."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"accept"},
        "guardrail_no_accept": False,
        "rationale": (
            "Offer of $59 beats the target of $65. Accept — countering risks losing "
            "an offer that already exceeded our goal."
        ),
    },
    {
        "name": "offer_between_target_and_walkaway_early_round",
        "reply": (
            "We can offer you a loyalty rate of $72/month. This is a discounted rate "
            "exclusively available to long-term customers like you."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter"},
        "guardrail_no_accept": False,
        "rationale": (
            "Offer of $72 is between target ($65) and walkaway ($80). Round 1 — "
            "there is room to push. Counter toward $65."
        ),
    },
    {
        "name": "offer_between_target_walkaway_late_final_language_small_gap",
        "reply": (
            "I've escalated this to our retention department. Our absolute best and "
            "final offer is $68/month — we genuinely cannot go any lower than this."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft",    "content": "Round 1: requested $65/month"},
            {"type": "reply_received", "content": "They countered at $75"},
            {"type": "email_draft",    "content": "Round 2: held at $65/month"},
            {"type": "reply_received", "content": "They countered at $70"},
            {"type": "email_draft",    "content": "Round 3: held at $65/month"},
        ],
        "expected": {"accept", "counter"},
        "guardrail_no_accept": False,
        "rationale": (
            "Round 3, explicit 'final offer' language, gap is only $3 from target. "
            "Accept is the pragmatic call; agent may also choose one final counter."
        ),
    },
    {
        "name": "offer_just_below_walkaway",
        "reply": (
            "We can bring your rate down to $79/month as a loyalty discount. "
            "This offer is available for the next 24 hours."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"accept", "counter"},
        "guardrail_no_accept": False,
        "rationale": (
            "Offer of $79 is just inside the walkaway threshold of $80. Both "
            "accepting the certain win and countering one more time are defensible."
        ),
    },
    {
        "name": "offer_above_walkaway",
        "reply": (
            "Thank you for being a loyal AT&T customer. We can offer you a $12 monthly "
            "discount, reducing your bill to $88/month."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter", "escalate"},
        "guardrail_no_accept": True,
        "rationale": (
            "Offer of $88 is above the walkaway threshold of $80. "
            "MUST NOT accept — counter or escalate to push for a real reduction."
        ),
    },
    {
        "name": "offer_far_above_walkaway_token_credit",
        "reply": (
            "We're happy to offer a one-time $5 account credit as a courtesy. "
            "Your regular rate of $100/month will continue after this month."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter", "escalate"},
        "guardrail_no_accept": True,
        "rationale": (
            "A one-time $5 credit is not a rate reduction. Effective monthly cost "
            "remains $100 — far above the $80 walkaway. Counter firmly or escalate."
        ),
    },
    {
        "name": "flat_refusal_no_offer",
        "reply": (
            "After reviewing your account, we regret to inform you that our rates are "
            "fixed and we are unable to offer discounts or promotional pricing."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"escalate", "close"},
        "guardrail_no_accept": False,
        "rationale": (
            "Explicit refusal with no offer or number. No basis for accepting or "
            "countering — escalate for human review or close the negotiation."
        ),
    },
    {
        "name": "vague_loyalty_talk_no_number",
        "reply": (
            "We appreciate your loyalty and truly want to keep you as a customer. "
            "We can look into options that might work better for your budget. "
            "Could you share more about what you're looking for?"
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter", "escalate"},
        "guardrail_no_accept": True,
        "rationale": (
            "Friendly language but zero concrete offer or dollar amount. "
            "Must NOT accept — there is nothing to accept."
        ),
    },
    {
        "name": "ambiguous_website_redirect_no_amount",
        "reply": (
            "We have various plans and packages that may suit your needs. "
            "Our promotions change monthly — please visit att.com/deals to explore "
            "current offers tailored to your area."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter", "escalate", "close"},
        "guardrail_no_accept": True,
        "rationale": (
            "Redirect to website with no dollar amount. No deal was offered. "
            "Must NOT treat this as an accepted negotiation."
        ),
    },
    {
        "name": "supervisor_stall_no_offer",
        "reply": (
            "Thank you for contacting AT&T retention. A supervisor will review your "
            "account and reach out within 5–7 business days. We appreciate your patience."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"escalate", "close"},
        "guardrail_no_accept": False,
        "rationale": (
            "Pure stall — no offer, just a promise to follow up. "
            "Escalate for a human to decide how to proceed, or close."
        ),
    },
    {
        "name": "insufficient_discount_still_above_walkaway",
        "reply": (
            "As a valued customer we're pleased to extend a 10% loyalty discount, "
            "bringing your monthly bill to $90. This is valid for the next 12 months."
        ),
        "strategy": {
            "target_price": 65.00,
            "walkaway_threshold": 80.00,
            "opening_position": "Request a reduction from $100 to $65/month",
            "key_arguments": ["Competitors charge $55–65/month for equivalent speed"],
        },
        "history": [
            {"type": "email_draft", "content": "Round 1: requested $65/month"},
        ],
        "expected": {"counter", "escalate"},
        "guardrail_no_accept": True,
        "rationale": (
            "$90 is above the $80 walkaway. A 10% discount is a start but well short "
            "of target. Counter firmly."
        ),
    },
]
