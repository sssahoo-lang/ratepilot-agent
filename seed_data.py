import json
import os
from datetime import datetime, timedelta


def demo_seed_enabled() -> bool:
    return os.getenv("SEED_DEMO_DATA", "").strip().lower() == "true"


DEMO_BILLS = [
    {
        "key": "xfinity-internet",
        "filename": "demo_xfinity_internet_bill.txt",
        "provider": "Comcast Xfinity",
        "current_amount": 118.40,
        "account_tenure": "4 years 2 months",
        "contract_end": "Month-to-month",
        "bill_type": "internet",
        "extracted_data": {
            "provider": "Comcast Xfinity",
            "bill_type": "internet",
            "current_amount": 118.40,
            "account_tenure": "4 years 2 months",
            "contract_end": "Month-to-month",
            "account_number": "1842",
            "services": ["Gigabit internet", "Gateway rental"],
            "payment_history": "good",
            "key_details": "Long-term customer with autopay and competing fiber service available nearby.",
        },
    },
    {
        "key": "verizon-wireless",
        "filename": "demo_verizon_wireless_bill.txt",
        "provider": "Verizon Wireless",
        "current_amount": 162.80,
        "account_tenure": "6 years",
        "contract_end": "No device payment contract",
        "bill_type": "phone",
        "extracted_data": {
            "provider": "Verizon Wireless",
            "bill_type": "phone",
            "current_amount": 162.80,
            "account_tenure": "6 years",
            "contract_end": "No device payment contract",
            "account_number": "9021",
            "services": ["Two unlimited lines", "International calling add-on"],
            "payment_history": "good",
            "key_details": "Two-line unlimited plan with loyalty tenure and cheaper comparable MVNO plans.",
        },
    },
    {
        "key": "geico-auto",
        "filename": "demo_geico_auto_policy.txt",
        "provider": "GEICO",
        "current_amount": 214.50,
        "account_tenure": "3 years 8 months",
        "contract_end": "Renews July 2026",
        "bill_type": "insurance",
        "extracted_data": {
            "provider": "GEICO",
            "bill_type": "insurance",
            "current_amount": 214.50,
            "account_tenure": "3 years 8 months",
            "contract_end": "Renews July 2026",
            "account_number": "4458",
            "services": ["Auto policy", "Collision", "Comprehensive"],
            "payment_history": "good",
            "key_details": "Safe driver discount eligible and competing quotes are lower.",
        },
    },
    {
        "key": "spectrum-internet",
        "filename": "demo_spectrum_internet_bill.txt",
        "provider": "Spectrum",
        "current_amount": 94.99,
        "account_tenure": "18 months",
        "contract_end": "Month-to-month",
        "bill_type": "internet",
        "extracted_data": {
            "provider": "Spectrum",
            "bill_type": "internet",
            "current_amount": 94.99,
            "account_tenure": "18 months",
            "contract_end": "Month-to-month",
            "account_number": "3310",
            "services": ["500 Mbps internet"],
            "payment_history": "unknown",
            "key_details": "Promotional rate expired recently.",
        },
    },
    {
        "key": "att-fiber",
        "filename": "demo_att_fiber_bill.txt",
        "provider": "AT&T Fiber",
        "current_amount": 89.00,
        "account_tenure": "2 years 1 month",
        "contract_end": "Month-to-month",
        "bill_type": "internet",
        "extracted_data": {
            "provider": "AT&T Fiber",
            "bill_type": "internet",
            "current_amount": 89.00,
            "account_tenure": "2 years 1 month",
            "contract_end": "Month-to-month",
            "account_number": "7704",
            "services": ["Fiber 500", "Autopay"],
            "payment_history": "good",
            "key_details": "Customer is eligible for competitor switch credits in the same market.",
        },
    },
    {
        "key": "spotify-family",
        "filename": "demo_spotify_family_plan.txt",
        "provider": "Spotify",
        "current_amount": 19.99,
        "account_tenure": "5 years",
        "contract_end": "Monthly subscription",
        "bill_type": "subscription",
        "extracted_data": {
            "provider": "Spotify",
            "bill_type": "subscription",
            "current_amount": 19.99,
            "account_tenure": "5 years",
            "contract_end": "Monthly subscription",
            "account_number": "1187",
            "services": ["Family plan"],
            "payment_history": "good",
            "key_details": "Long-tenured subscriber asking for retention promotion.",
        },
    },
]


DEMO_NEGOTIATIONS = [
    {
        "bill_key": "xfinity-internet",
        "status": "won",
        "target_price": 72.00,
        "walkaway_threshold": 95.00,
        "savings_achieved": 38.41,
        "best_offer_received": 79.99,
        "rounds_count": 2,
        "days_ago": 1,
        "research": {
            "competitor_prices": [
                {"provider": "AT&T Fiber", "price": 65.00, "plan": "Fiber 500", "promo": "Autopay discount"},
                {"provider": "T-Mobile Home Internet", "price": 50.00, "plan": "5G home internet", "promo": "Price lock"},
                {"provider": "Verizon 5G Home", "price": 60.00, "plan": "5G home plus", "promo": "Bundle discount"},
            ],
            "market_average": 58.33,
            "current_promotions": ["Retention credits available for autopay customers"],
            "price_trend": "stable",
            "leverage_points": ["Comparable plans are $50-$65/mo", "Customer is out of contract", "Excellent payment history"],
            "recommended_target": 72.00,
            "walkaway_threshold": 95.00,
            "research_summary": "Comparable internet offers in the area are materially lower than the current bill.",
        },
        "strategy": {
            "opening_ask": 65.00,
            "target_price": 72.00,
            "walkaway_threshold": 95.00,
            "primary_leverage": "Competing fiber and 5G home internet offers are available below $65/mo.",
            "leverage_points": ["Out-of-contract account", "Four-year tenure", "Autopay and strong payment history"],
            "tone": "firm",
            "key_phrases": ["match current market pricing", "retain a long-term customer"],
            "anticipated_responses": [
                {"response_type": "partial_offer", "counter_strategy": "Ask for a 12-month retention credit"},
                {"response_type": "acceptance", "counter_strategy": "Accept if under walkaway threshold"},
            ],
            "strategy_summary": "Anchor at nearby fiber pricing and accept a meaningful retention credit.",
        },
        "steps": [
            {
                "type": "research",
                "hours_after": 0,
                "content": "research",
                "reasoning": "Searched comparable internet plans and recent retention promotions.",
                "decision": "Market average: $58.33",
            },
            {
                "type": "strategy",
                "hours_after": 1,
                "content": "strategy",
                "reasoning": "Built a firm but low-friction retention strategy.",
                "decision": "Target: $72.00",
            },
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Request to lower Xfinity internet rate",
                    "body": "Hello,\n\nI have been an Xfinity customer for over four years and my current internet bill is $118.40/month. AT&T Fiber and 5G home internet options in my area are currently advertised between $50 and $65/month. I would like to keep my service with Xfinity, but I need the monthly rate brought closer to market pricing.\n\nCan you apply a loyalty or retention discount to bring my plan near $72/month?\n\nThank you,\nRatePilot Demo Customer\nAccount ending 1842",
                    "key_arguments_used": ["Long-term customer", "Competitor pricing", "Month-to-month flexibility"],
                    "ask_amount": 72.00,
                    "reasoning": "Anchors below the target while staying grounded in competitor pricing.",
                },
                "reasoning": "Drafted the opening retention request.",
                "decision": "Asking: $72.00/month",
            },
            {
                "type": "reply_received",
                "hours_after": 8,
                "content": {
                    "reply": "We can apply a 12-month loyalty promotion and reduce your internet plan to $84.99/month.",
                    "interpretation": {
                        "classification": "partial_offer",
                        "offered_amount": 84.99,
                        "decision": "counter",
                        "decision_reasoning": "The offer is below the walkaway threshold but still above the target.",
                    },
                },
                "reasoning": "Offer improved the bill but left room for a loyalty credit.",
                "decision": "counter",
            },
            {
                "type": "email_draft",
                "hours_after": 9,
                "content": {
                    "subject": "Re: Request to lower Xfinity internet rate",
                    "body": "Thank you for the $84.99 loyalty offer. I appreciate the movement, but competing services are still available at $65/month or less. If you can bring the rate to $79.99/month for 12 months, I can keep the account active today.\n\nBest,\nRatePilot Demo Customer\nAccount ending 1842",
                    "key_arguments_used": ["Acknowledged offer", "Clear accept price", "Immediate retention"],
                    "ask_amount": 79.99,
                    "reasoning": "Counters just below the first offer to close quickly.",
                },
                "reasoning": "Drafted a closeable counter-offer.",
                "decision": "Counter: $79.99",
            },
            {
                "type": "closed",
                "hours_after": 12,
                "content": {"outcome": "won", "final_amount": 79.99},
                "reasoning": "Accepted the provider's revised loyalty rate.",
                "decision": "DEAL CLOSED",
            },
        ],
    },
    {
        "bill_key": "verizon-wireless",
        "status": "won",
        "target_price": 129.00,
        "walkaway_threshold": 145.00,
        "savings_achieved": 33.80,
        "best_offer_received": 129.00,
        "rounds_count": 1,
        "days_ago": 3,
        "research": {
            "competitor_prices": [
                {"provider": "Visible", "price": 70.00, "plan": "Two unlimited lines", "promo": "Taxes included"},
                {"provider": "Mint Mobile", "price": 90.00, "plan": "Two unlimited lines", "promo": "Intro rate"},
                {"provider": "T-Mobile", "price": 140.00, "plan": "Essentials Saver", "promo": "Autopay discount"},
            ],
            "market_average": 100.00,
            "current_promotions": ["Loyalty discounts for multi-line customers"],
            "price_trend": "stable",
            "leverage_points": ["No device payoff obligation", "Two lines can port out immediately", "Six-year account tenure"],
            "recommended_target": 129.00,
            "walkaway_threshold": 145.00,
            "research_summary": "The current wireless plan is high compared with both MVNO and carrier-owned alternatives.",
        },
        "strategy": {
            "opening_ask": 120.00,
            "target_price": 129.00,
            "walkaway_threshold": 145.00,
            "primary_leverage": "The customer can move two paid-off lines to lower-cost carriers without penalty.",
            "leverage_points": ["Six-year tenure", "No contract lock-in", "Lower competing unlimited offers"],
            "tone": "collaborative",
            "key_phrases": ["keep both lines with Verizon", "loyalty discount"],
            "anticipated_responses": [{"response_type": "partial_offer", "counter_strategy": "Accept if at or below $129"}],
            "strategy_summary": "Emphasize retention of both lines and ask for loyalty pricing.",
        },
        "steps": [
            {"type": "research", "hours_after": 0, "content": "research", "reasoning": "Compared carrier and MVNO unlimited plans.", "decision": "Market average: $100.00"},
            {"type": "strategy", "hours_after": 1, "content": "strategy", "reasoning": "Focused on the no-contract ability to port out.", "decision": "Target: $129.00"},
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Loyalty discount request for two-line account",
                    "body": "Hello Verizon team,\n\nMy two-line account is currently $162.80/month. I have kept these lines with Verizon for six years, but comparable unlimited options are significantly lower and there is no device payoff preventing me from switching. I would prefer to stay if you can apply loyalty pricing around $129/month.\n\nThank you,\nRatePilot Demo Customer\nAccount ending 9021",
                    "key_arguments_used": ["Six-year tenure", "Two-line retention", "No device contract"],
                    "ask_amount": 129.00,
                    "reasoning": "Uses retention risk without sounding adversarial.",
                },
                "reasoning": "Drafted opening email.",
                "decision": "Asking: $129.00/month",
            },
            {
                "type": "reply_received",
                "hours_after": 7,
                "content": {
                    "reply": "We can add a loyalty discount and autopay credit to bring the account to $129/month.",
                    "interpretation": {
                        "classification": "accepted",
                        "offered_amount": 129.00,
                        "decision": "accept",
                        "decision_reasoning": "The offer meets the target price.",
                    },
                },
                "reasoning": "Offer met the target exactly.",
                "decision": "accept",
            },
            {"type": "closed", "hours_after": 8, "content": {"outcome": "won", "final_amount": 129.00}, "reasoning": "Accepted the loyalty and autopay discount.", "decision": "DEAL CLOSED"},
        ],
    },
    {
        "bill_key": "geico-auto",
        "status": "awaiting_reply",
        "target_price": 172.00,
        "walkaway_threshold": 190.00,
        "savings_achieved": 0,
        "best_offer_received": 189.00,
        "rounds_count": 1,
        "days_ago": 5,
        "research": {
            "competitor_prices": [
                {"provider": "Progressive", "price": 181.00, "plan": "Comparable auto policy", "promo": "Snapshot discount"},
                {"provider": "State Farm", "price": 193.00, "plan": "Comparable coverage", "promo": "Safe driver discount"},
                {"provider": "Allstate", "price": 198.00, "plan": "Comparable coverage", "promo": "Bundle discount"},
            ],
            "market_average": 190.67,
            "current_promotions": ["Safe driver and defensive driving discounts"],
            "price_trend": "rising",
            "leverage_points": ["Safe driver record", "Competing quote below current premium", "Policy renewal upcoming"],
            "recommended_target": 172.00,
            "walkaway_threshold": 190.00,
            "research_summary": "Competitor quotes show room for a retention adjustment before renewal.",
        },
        "strategy": {
            "opening_ask": 172.00,
            "target_price": 172.00,
            "walkaway_threshold": 190.00,
            "primary_leverage": "A comparable Progressive quote is $33.50/month lower.",
            "leverage_points": ["Renewal window", "Safe driver record", "Competing quote"],
            "tone": "collaborative",
            "key_phrases": ["review my policy discounts", "match a comparable quote"],
            "anticipated_responses": [{"response_type": "partial_offer", "counter_strategy": "Ask for safe-driver review"}],
            "strategy_summary": "Ask GEICO to review discounts before renewal and match a lower quote.",
        },
        "steps": [
            {"type": "research", "hours_after": 0, "content": "research", "reasoning": "Compared auto policy quotes and eligible discounts.", "decision": "Market average: $190.67"},
            {"type": "strategy", "hours_after": 1, "content": "strategy", "reasoning": "Built a renewal-window discount review strategy.", "decision": "Target: $172.00"},
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Policy discount review before renewal",
                    "body": "Hello GEICO team,\n\nMy auto policy is renewing soon at $214.50/month. I have a clean driving record and have received a comparable quote at $181/month. Before I move coverage, can you review my safe-driver and retention discounts and bring this closer to $172/month?\n\nThank you,\nRatePilot Demo Customer\nPolicy ending 4458",
                    "key_arguments_used": ["Upcoming renewal", "Clean record", "Lower quote"],
                    "ask_amount": 172.00,
                    "reasoning": "Creates urgency before renewal while inviting a discount review.",
                },
                "reasoning": "Drafted opening insurance review request.",
                "decision": "Asking: $172.00/month",
            },
            {
                "type": "reply_received",
                "hours_after": 20,
                "content": {
                    "reply": "After review, we can lower the premium to $189/month if you complete the defensive driving certification.",
                    "interpretation": {
                        "classification": "partial_offer",
                        "offered_amount": 189.00,
                        "decision": "counter",
                        "decision_reasoning": "The offer is under walkaway but requires an extra step; ask for a better immediate adjustment.",
                    },
                },
                "reasoning": "Tracked the first concrete offer and prepared a follow-up.",
                "decision": "counter",
            },
            {
                "type": "email_draft",
                "hours_after": 21,
                "content": {
                    "subject": "Re: Policy discount review before renewal",
                    "body": "Thank you for reviewing the policy. The $189/month option helps, but it still leaves the policy above my comparable quote after requiring an extra certification. If you can apply an immediate retention adjustment to $179/month, I can keep the renewal with GEICO.\n\nBest,\nRatePilot Demo Customer\nPolicy ending 4458",
                    "key_arguments_used": ["Acknowledged offer", "Comparable quote", "Immediate retention"],
                    "ask_amount": 179.00,
                    "reasoning": "Counters below the offered rate while staying above the strongest competitor quote.",
                },
                "reasoning": "Drafted a follow-up counter.",
                "decision": "Counter: $179.00",
            },
        ],
    },
    {
        "bill_key": "spectrum-internet",
        "status": "closed_no_deal",
        "target_price": 64.99,
        "walkaway_threshold": 82.00,
        "savings_achieved": 0,
        "best_offer_received": None,
        "rounds_count": 1,
        "days_ago": 8,
        "research": {
            "competitor_prices": [
                {"provider": "T-Mobile Home Internet", "price": 50.00, "plan": "5G home internet", "promo": "Price lock"},
                {"provider": "Frontier Fiber", "price": 59.99, "plan": "Fiber 500", "promo": "New customer rate"},
            ],
            "market_average": 54.99,
            "current_promotions": [],
            "price_trend": "stable",
            "leverage_points": ["Promo expired", "No contract", "Competing home internet alternatives"],
            "recommended_target": 64.99,
            "walkaway_threshold": 82.00,
            "research_summary": "Competing internet options were below the current Spectrum rate.",
        },
        "strategy": {
            "opening_ask": 59.99,
            "target_price": 64.99,
            "walkaway_threshold": 82.00,
            "primary_leverage": "New customer fiber and 5G internet pricing is substantially lower.",
            "leverage_points": ["Month-to-month status", "Expired promo", "Competitor rates"],
            "tone": "firm",
            "key_phrases": ["promotional rate expired", "match market pricing"],
            "anticipated_responses": [{"response_type": "rejection", "counter_strategy": "Close and recommend calling retention"}],
            "strategy_summary": "Push for restoration of promotional pricing, but close if no discount is available.",
        },
        "steps": [
            {"type": "research", "hours_after": 0, "content": "research", "reasoning": "Benchmarked nearby internet alternatives.", "decision": "Market average: $54.99"},
            {"type": "strategy", "hours_after": 1, "content": "strategy", "reasoning": "Built a promo-restoration request.", "decision": "Target: $64.99"},
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Request to restore promotional internet rate",
                    "body": "Hello Spectrum team,\n\nMy internet rate increased to $94.99/month after my promotion expired. Comparable home internet plans are currently advertised around $50-$60/month. Can you restore a promotional or loyalty rate around $64.99/month so I can keep the account active?\n\nThank you,\nRatePilot Demo Customer\nAccount ending 3310",
                    "key_arguments_used": ["Expired promo", "Competitor pricing", "Retention request"],
                    "ask_amount": 64.99,
                    "reasoning": "Requests a realistic restoration rather than cancellation threat.",
                },
                "reasoning": "Drafted opening request.",
                "decision": "Asking: $64.99/month",
            },
            {
                "type": "reply_received",
                "hours_after": 12,
                "content": {
                    "reply": "There are no current promotions available for this account.",
                    "interpretation": {
                        "classification": "rejected",
                        "offered_amount": None,
                        "decision": "close",
                        "decision_reasoning": "No concrete discount or escalation path was offered.",
                    },
                },
                "reasoning": "Provider did not present a concrete offer.",
                "decision": "close",
            },
            {"type": "closed", "hours_after": 13, "content": {"outcome": "no_deal"}, "reasoning": "Closed after no retention offer was provided.", "decision": "CLOSED"},
        ],
    },
    {
        "bill_key": "att-fiber",
        "status": "awaiting_reply",
        "target_price": 60.00,
        "walkaway_threshold": 76.00,
        "savings_achieved": 0,
        "best_offer_received": None,
        "rounds_count": 0,
        "days_ago": 10,
        "research": {
            "competitor_prices": [
                {"provider": "T-Mobile Home Internet", "price": 50.00, "plan": "5G home internet", "promo": "Price lock"},
                {"provider": "Xfinity", "price": 55.00, "plan": "Internet promo", "promo": "12-month new customer pricing"},
                {"provider": "Verizon 5G Home", "price": 60.00, "plan": "5G home internet", "promo": "Autopay discount"},
            ],
            "market_average": 55.00,
            "current_promotions": ["Autopay and paperless billing credits"],
            "price_trend": "stable",
            "leverage_points": ["Multiple lower alternatives", "Existing autopay", "Month-to-month service"],
            "recommended_target": 60.00,
            "walkaway_threshold": 76.00,
            "research_summary": "The account is above market for comparable home internet offers.",
        },
        "strategy": {
            "opening_ask": 55.00,
            "target_price": 60.00,
            "walkaway_threshold": 76.00,
            "primary_leverage": "Nearby 5G and cable internet options advertise lower monthly rates.",
            "leverage_points": ["Autopay customer", "Month-to-month", "Multiple competitors"],
            "tone": "collaborative",
            "key_phrases": ["keep my fiber service", "align with market rate"],
            "anticipated_responses": [{"response_type": "partial_offer", "counter_strategy": "Ask for bill credit or 12-month promo"}],
            "strategy_summary": "Ask for a retention credit while emphasizing preference for fiber service.",
        },
        "steps": [
            {"type": "research", "hours_after": 0, "content": "research", "reasoning": "Collected lower home internet offers in the same market.", "decision": "Market average: $55.00"},
            {"type": "strategy", "hours_after": 1, "content": "strategy", "reasoning": "Built a retention-credit strategy.", "decision": "Target: $60.00"},
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Fiber account retention pricing request",
                    "body": "Hello AT&T team,\n\nI like my fiber service, but my current $89/month bill is above comparable internet offers in my area. I am seeing alternatives around $50-$60/month. Can you apply a retention promotion or bill credit to bring my Fiber 500 plan near $60/month?\n\nThank you,\nRatePilot Demo Customer\nAccount ending 7704",
                    "key_arguments_used": ["Preference to stay", "Comparable rates", "Retention promotion"],
                    "ask_amount": 60.00,
                    "reasoning": "Keeps the ask friendly and focused on alignment with market pricing.",
                },
                "reasoning": "Drafted opening retention request.",
                "decision": "Asking: $60.00/month",
            },
        ],
    },
    {
        "bill_key": "spotify-family",
        "status": "won",
        "target_price": 16.99,
        "walkaway_threshold": 19.99,
        "savings_achieved": 3.00,
        "best_offer_received": 16.99,
        "rounds_count": 1,
        "days_ago": 14,
        "research": {
            "competitor_prices": [
                {"provider": "Apple Music", "price": 16.99, "plan": "Family plan", "promo": "One-month trial"},
                {"provider": "YouTube Music", "price": 16.99, "plan": "Family plan", "promo": "Trial available"},
            ],
            "market_average": 16.99,
            "current_promotions": ["Win-back and student offers vary by account"],
            "price_trend": "rising",
            "leverage_points": ["Five-year tenure", "Comparable family plans cost less", "Low-friction cancellation"],
            "recommended_target": 16.99,
            "walkaway_threshold": 19.99,
            "research_summary": "Comparable family subscription plans are available for $16.99/month.",
        },
        "strategy": {
            "opening_ask": 16.99,
            "target_price": 16.99,
            "walkaway_threshold": 19.99,
            "primary_leverage": "Comparable family plans are $3/month lower.",
            "leverage_points": ["Long tenure", "Easy subscription cancellation", "Direct competitor pricing"],
            "tone": "collaborative",
            "key_phrases": ["retain a long-time family subscriber", "match comparable family pricing"],
            "anticipated_responses": [{"response_type": "acceptance", "counter_strategy": "Accept if $16.99"}],
            "strategy_summary": "Ask for a small retention credit based on comparable subscription pricing.",
        },
        "steps": [
            {"type": "research", "hours_after": 0, "content": "research", "reasoning": "Compared family music subscriptions.", "decision": "Market average: $16.99"},
            {"type": "strategy", "hours_after": 1, "content": "strategy", "reasoning": "Built a low-friction subscription retention ask.", "decision": "Target: $16.99"},
            {
                "type": "email_draft",
                "hours_after": 2,
                "content": {
                    "subject": "Family plan retention discount request",
                    "body": "Hello Spotify support,\n\nI have been on Spotify for five years and currently pay $19.99/month for the Family plan. Comparable family music plans are available at $16.99/month. Can you apply a retention credit or promotional rate to match $16.99/month?\n\nThank you,\nRatePilot Demo Customer\nAccount ending 1187",
                    "key_arguments_used": ["Five-year tenure", "Comparable pricing", "Clear match request"],
                    "ask_amount": 16.99,
                    "reasoning": "Small, specific ask likely to be accepted or offered as a promo.",
                },
                "reasoning": "Drafted subscription retention request.",
                "decision": "Asking: $16.99/month",
            },
            {
                "type": "reply_received",
                "hours_after": 6,
                "content": {
                    "reply": "We can apply a three-month promotional credit that brings your Family plan to $16.99/month.",
                    "interpretation": {
                        "classification": "accepted",
                        "offered_amount": 16.99,
                        "decision": "accept",
                        "decision_reasoning": "The promotion meets the target price.",
                    },
                },
                "reasoning": "Offer met the target price.",
                "decision": "accept",
            },
            {"type": "closed", "hours_after": 7, "content": {"outcome": "won", "final_amount": 16.99}, "reasoning": "Accepted the promotional credit.", "decision": "DEAL CLOSED"},
        ],
    },
]


async def seed_demo_data(db) -> None:
    if not demo_seed_enabled():
        print("Demo data seeding skipped. Set SEED_DEMO_DATA=true to enable.")
        return

    async with db.execute("SELECT COUNT(*) FROM negotiations") as cursor:
        row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    base_time = datetime.now().replace(microsecond=0)
    bill_ids = {}

    for bill in DEMO_BILLS:
        extracted_data = dict(bill["extracted_data"])
        raw_text = (
            f"Demo bill for {bill['provider']} showing a current monthly amount "
            f"of ${bill['current_amount']:.2f}."
        )
        cursor = await db.execute(
            """
            INSERT INTO bills (
                filename, provider, current_amount, account_tenure,
                contract_end, bill_type, raw_text, extracted_data, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill["filename"],
                bill["provider"],
                bill["current_amount"],
                bill["account_tenure"],
                bill["contract_end"],
                bill["bill_type"],
                raw_text,
                json.dumps(extracted_data),
                (base_time - timedelta(days=16)).isoformat(),
            ),
        )
        bill_ids[bill["key"]] = cursor.lastrowid

    for negotiation in DEMO_NEGOTIATIONS:
        created_at = base_time - timedelta(days=negotiation["days_ago"])
        updated_at = created_at + timedelta(hours=max(step["hours_after"] for step in negotiation["steps"]))
        cursor = await db.execute(
            """
            INSERT INTO negotiations (
                bill_id, status, target_price, walkaway_threshold, savings_achieved,
                best_offer_received, rounds_count, research_findings, strategy,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bill_ids[negotiation["bill_key"]],
                negotiation["status"],
                negotiation["target_price"],
                negotiation["walkaway_threshold"],
                negotiation["savings_achieved"],
                negotiation["best_offer_received"],
                negotiation["rounds_count"],
                json.dumps(negotiation["research"]),
                json.dumps(negotiation["strategy"]),
                created_at.isoformat(),
                updated_at.isoformat(),
            ),
        )
        negotiation_id = cursor.lastrowid

        for step in negotiation["steps"]:
            if step["content"] == "research":
                content = negotiation["research"]
            elif step["content"] == "strategy":
                content = negotiation["strategy"]
            else:
                content = step["content"]

            await db.execute(
                """
                INSERT INTO negotiation_steps (
                    negotiation_id, step_type, content, reasoning, decision, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    negotiation_id,
                    step["type"],
                    json.dumps(content),
                    step["reasoning"],
                    step["decision"],
                    (created_at + timedelta(hours=step["hours_after"])).isoformat(),
                ),
            )

    await db.commit()
